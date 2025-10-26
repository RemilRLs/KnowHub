import logging
import time 



from fastapi import APIRouter, HTTPException
from dramatiq.results import ResultTimeout, ResultMissing

from app.api.v1.schemas.generate import GenerateRequest, GenerateResponse, GenerationResult
from app.api.v1.schemas.ingest import JobStatusReq
from app.tasks.generate import generate_answer
# Redis
from app.core.redis_config import redis_client
from app.tasks import results_backend

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/generate", response_model=GenerateResponse)
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
    

@router.post("/generate/status")
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
            logger.warning(f"Generation job {req.job_id} not found")
            return {
                "job_id": req.job_id,
                "status": "not_found",
                "message": "Job not found or expired"
            }
            
    except Exception as e:
        logger.error(f"Error checking generation job status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check job status: {str(e)}"
        )