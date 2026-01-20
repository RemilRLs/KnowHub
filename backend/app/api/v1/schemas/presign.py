from pydantic import BaseModel, Field

from typing import Dict, Optional, List

class PresignReq(BaseModel):
    filename: str
    collection: str # TODO : To delete
    content_type: Optional[str] = None

class BatchPresignReq(BaseModel):
    collection: str
    files: List[PresignReq]

class PresignResp(BaseModel):
    doc_id: str
    s3_key: str
    upload_url: str
    headers: Dict[str, str]
    expires_in: int

class BatchPresignResp(BaseModel):
    items: List[PresignResp]

class EnqueueReq(BaseModel):
    doc_id: str
    s3_key: str
    filename: str
    collection: str # TODO: To delete
    checksum_sha256: str = Field(
        description="SHA-256 checksum of the file to be uploaded to verify integrity."
    )

class EnqueueBatchReq(BaseModel):
    collection: str
    items: List[EnqueueReq]
    
class EnqueueBatchResp(BaseModel):
    collection: str
    job_ids: List[str]
    file_refused: List[str]
    queue: Optional[str] = None

class EnqueueReq(BaseModel):
    doc_id: str
    s3_key: str
    filename: str
    collection: str
    checksum_sha256: Optional[str] = None 