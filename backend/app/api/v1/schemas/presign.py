from pydantic import BaseModel, Field

from typing import Optional

class PresignReq(BaseModel):
    filename: str
    collection: str
    content_type: Optional[str] = None

class PresignResp(BaseModel):
    doc_id: str
    s3_key: str
    upload_url: str
    expires_in: int
    headers: dict

class EnqueueReq(BaseModel):
    doc_id: str
    s3_key: str
    filename: str
    collection: str
    checksum_sha256: str = Field(
        description="SHA-256 checksum of the file to be uploaded to verify integrity."
    )

class EnqueueReq(BaseModel):
    doc_id: str
    s3_key: str
    filename: str
    collection: str
    checksum_sha256: Optional[str] = None 