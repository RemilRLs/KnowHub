from pydantic import BaseModel, Field

class JobStatusReq(BaseModel):
    job_id: str
    queue: str
    wait_ms: int = Field(0, description="Milliseconds to wait for the job to complete before returning a timeout status.")
