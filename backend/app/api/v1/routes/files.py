import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.minio_client import MinioClient
from app.api.v1.schemas.download import DownloadUrlResponse


router = APIRouter()
logger = logging.getLogger(__name__)

minio_client = MinioClient()


@router.get("/download", response_model=DownloadUrlResponse)
def get_download_url(
    key: str = Query(...),
    expires_in: int = Query(600, ge=60, le=3600),
):
    if not key.startswith("processed/"):
        raise HTTPException(status_code=400, detail="Invalid key prefix")

    if not minio_client.object_exists(key):
        raise HTTPException(status_code=404, detail="File not found")

    url = minio_client.presigned_get_url(key=key, expires_seconds=expires_in)
    logger.info("Generated presigned download URL for key=%s", key)

    return DownloadUrlResponse(key=key, url=url, expires_in=expires_in)
