from pydantic import BaseModel, Field

class JobStatusReq(BaseModel):
    job_id: str
    queue: str | None = Field(
        None,
        description="Optional queue name; reserved for future use."
    )
    actor_name: str | None = Field(
        None,
        description="Optional actor name to help identify the job."
    )
    wait_ms: int = Field(
        0,
        description="Milliseconds to wait for the job to complete before returning a timeout status."
    )

class EmbedRequest(BaseModel):
    texts: list[str]

class EmbedResponse(BaseModel):
    embeddings: list[list[float]]