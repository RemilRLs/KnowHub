from pydantic import BaseModel


class DownloadUrlResponse(BaseModel):
    key: str
    url: str
    expires_in: int
