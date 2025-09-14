import io, os

from pathlib import Path

from minio import Minio
from minio.error import S3Error

from typing import Optional, Tuple

class MinioClient:
    def __init__(self):
        """
        Initializes the Minio client with configuration from environment variables.
        Environment Variables:
            MINIO_ENDPOINT (str): The MinIO server endpoint. Defaults to "localhost:9000".
            MINIO_ROOT_USER (str): The access key for MinIO authentication.
            MINIO_ROOT_PASSWORD (str): The secret key for MinIO authentication.
            MINIO_BUCKET (str): The name of the bucket to use or create. Defaults to "knowhub".
            MINIO_SECURE (str): Whether to use a secure (HTTPS) connection. Defaults to "false".
        Actions:
            - Creates a Minio client instance with the provided credentials and endpoint.
            - Checks if the specified bucket exists; if not, creates it.
        """
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ROOT_USER", "")
        self.secret_key = os.getenv("MINIO_ROOT_PASSWORD", "")
        self.bucket = os.getenv("MINIO_BUCKET", "knowhub")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)


    def get_file(
        self, key: str, dest_path: str, mkdirs: bool = True, overwrite: bool = True
    ) -> Tuple[Path, dict]:
        dest = Path(dest_path)
        if mkdirs:
            dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and not overwrite:
            raise FileExistsError(f"Destination exists: {dest}")

        try:
            stat = self.client.stat_object(self.bucket, key)
            meta = {
                "size": stat.size,
                "etag": stat.etag,
                "content_type": getattr(stat, "content_type", None),
                "last_modified": stat.last_modified.isoformat() if getattr(stat, "last_modified", None) else None,
            }
            self.client.fget_object(self.bucket, key, str(dest))
            return dest, meta
        except S3Error as e:
            raise RuntimeError(f"MinIO download failed for key '{key}': {e}") from e


    def put_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> str:
        """
        Uploads a bytes object to the configured MinIO bucket with the specified key.
        Args:
            key (str): The object key (path/name) under which the data will be stored in the bucket.
            data (bytes): The binary data to upload.
            content_type (Optional[str], optional): The MIME type of the object. Defaults to "application/octet-stream" if not provided.
        Returns:
            str: The S3 URI of the uploaded object in the format "s3://{bucket}/{key}".
        """
        
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("put_bytes expects 'bytes' or 'bytearray'.")
        try:
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=key,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type or "application/octet-stream",
            )
            return f"s3://{self.bucket}/{key}"
        except S3Error as e:
            raise RuntimeError(f"MinIO upload failed for key '{key}': {e}") from e