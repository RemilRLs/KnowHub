from pydantic import BaseModel, Field
from typing import Optional, List

class GenerateRequest(BaseModel):
    query: str
    collection: str 
    k: int = 10
    sources: Optional[List[str]] = None
    temperature: float = 0.5

class GenerateStreamRequest(BaseModel):
    query: str
    collection: str
    k: int = 10
    sources: Optional[List[str]] = None
    temperature: float = 0.5



class GenerateResponse(BaseModel):
    """
    Response for RAG generation job submission.
    """
    job_id: str
    status: str
    message: str

class GenerationResult(BaseModel):
    """
    Final generation result.
    """
    query: str
    answer: str
    sources: List[dict]
    retrieved_chunks: int
    generation_time_ms: float
    retrieval_time_ms: float