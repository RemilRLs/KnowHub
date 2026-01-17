import json
import logging
import time 

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from dramatiq.results import ResultTimeout, ResultMissing

from app.api.v1.schemas.generate import GenerateRequest, GenerateResponse, GenerationResult, GenerateStreamRequest
from app.api.v1.schemas.ingest import JobStatusReq
from app.tasks.generate import generate_answer, generate_answer_stream, STREAM_PREFIX
# Redis
from app.core.redis_config import redis_client
from app.tasks import results_backend



router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=GenerateResponse)
def generate_endpoint(req: GenerateRequest) -> GenerateResponse:
    """
    Submits a RAG generation job to the worker queue.
    
    Args:
        req: Generation request with query and parameters
        
    Returns:
        Job information with job_id for status checking
    """
    try:
        logger.info(f"Submitting generation job for query: '{req.query[:50]}...'")
        
        # Send job to Dramatiq worker
        message = generate_answer.send(
            query=req.query,
            collection=req.collection,
            k=req.k,
            sources=req.sources,
            temperature=req.temperature
        )

        job_id = message.message_id
        logger.info(f"Generation job submitted with ID: {job_id}")

        return GenerateResponse(
            job_id=job_id,
            status="pending",
            message=f"Generation job submitted successfully. Use job_id to check status."
        )
        
    except Exception as e:
        logger.error(f"Error submitting generation job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit generation job: {str(e)}"
        )


@router.get("/stream")
def stream_generate(req: GenerateStreamRequest = Depends()):
    job_id = f"stream-{int(time.time() * 1000)}-{id(req)}"
    stream_key = f"{STREAM_PREFIX}:{job_id}"

    generate_answer_stream.send(
        job_id=job_id,
        query=req.query,
        collection=req.collection,
        k=req.k,
        sources=req.sources,
        temperature=req.temperature,
    )

    def event_stream():
        last_id = "0-0"
        try:
            while True:
                results = redis_client.xread(
                    {stream_key: last_id},
                    block=1000,
                    count=10,
                )
                if not results:
                    continue

                _, entries = results[0]
                for entry_id, data in entries:
                    last_id = entry_id
                    event_type = data.get("type", "token")
                    payload_data = data.get("data", "")

                    try:
                        payload_data = json.loads(payload_data) if payload_data else ""
                    except json.JSONDecodeError:
                        pass

                    if event_type == "token":
                        payload = json.dumps({"token": payload_data}, ensure_ascii=False)
                        yield f"data: {payload}\n\n"
                    else:
                        payload = json.dumps(payload_data, ensure_ascii=False)
                        yield f"event: {event_type}\ndata: {payload}\n\n"
                        if event_type in {"done", "error"}:
                            return
        except Exception as e:
            logger.error(f"Error streaming generation: {str(e)}", exc_info=True)
            payload = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {payload}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=headers,
    )

    

@router.post("/status")
def get_generation_status(req: JobStatusReq):
    """
    Checks the status of a generation job.
    
    Args:
        req: Job status request with job_id
        
    Returns:
        Job status and result if completed
    """
    try:
        logger.info(f"Checking status for generation job: {req.job_id}")
        
        # Get message from backend
        message = generate_answer.message().copy(message_id=req.job_id)
        
        try:

            result = results_backend.get_result(message, block=False)
            logger.info(f"Generation job {req.job_id} completed successfully")
            
            return {
                "job_id": req.job_id,
                "status": "completed",
                "result": result
            }
            
        except ResultTimeout:
            logger.info(f"Generation job {req.job_id} still pending (timeout)")
            return {
                "job_id": req.job_id,
                "status": "pending",
                "message": "Job is still processing"
            }
            
        except ResultMissing:
            # If the result is missing, it likely means the job is still in the queue or processing
            # but hasn't finished yet. For polling purposes, we treat this as pending.
            logger.info(f"Generation job {req.job_id} result missing (likely pending)")
            return {
                "job_id": req.job_id,
                "status": "pending",
                "message": "Job is processing"
            }
            
    except Exception as e:
        logger.error(f"Error checking generation job status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check job status: {str(e)}"
        )