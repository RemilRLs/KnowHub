import io, os

from pathlib import Path

from minio import Minio
from minio.error import S3Error

from typing import Optional, Tuple
from datetime import timedelta

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
        self.internal_endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000") 
        self.public_endpoint   = os.getenv("MINIO_PUBLIC_ENDPOINT", self.internal_endpoint)
        self.access_key = os.getenv("MINIO_ROOT_USER", "")
        self.secret_key = os.getenv("MINIO_ROOT_PASSWORD", "")
        self.bucket = os.getenv("MINIO_BUCKET", "knowhub")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

        print(f"MinioClient init: endpoint={self.internal_endpoint}, public_endpoint={self.public_endpoint}, bucket={self.bucket}, secure={self.secure}")

        self.client = Minio(
            self.internal_endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

        self.public_client = Minio(
            self.public_endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)



    def presigned_put_url(self, key: str, expires_seconds: int = 600) -> str:
        """
        Generates a presigned URL for uploading an object to the specified bucket with the given key.
        Args:
            key (str): The object key (path/name) under which the data will be stored in the bucket.
            expires_seconds (int, optional): The number of seconds until the presigned URL expires. Defaults to 600 seconds (10 minutes).
            content_type (Optional[str], optional): The MIME type of the object. If provided, it will be included in the presigned URL.
        Returns:
            str: A presigned URL that can be used to upload an object to the specified bucket and key.
        """
        return self.public_client.presigned_put_object(
            self.bucket,
            key,
            expires=timedelta(seconds=expires_seconds),
        )
    
    def presigned_get_url(self, key: str, expires_seconds: int = 600) -> str:
        """
        Generates a presigned URL for downloading an object from the specified bucket with the given key.
        Args:
            key (str): The object key (path/name) of the data to be retrieved from the bucket.
            expires_seconds (int, optional): The number of seconds until the presigned URL expires. Defaults to 600 seconds (10 minutes).
        Returns:
            str: A presigned URL that can be used to download an object from the specified bucket and key.
        """
        return self.public_client.presigned_get_object(
            self.bucket,
            key,
            expires=timedelta(seconds=expires_seconds),
        )
    
    def object_exists(self, key: str) -> bool:
        """
        Checks if an object with the specified key exists in the configured MinIO bucket.
        Args:
            key (str): The object key (path/name) to check for existence in the bucket.
        Returns:
            bool: True if the object exists, False otherwise.
        """
        try:
            self.client.stat_object(self.bucket, key)
            return True
        except S3Error as e:
            return False

    def get_file(
        self, key: str, dest_path: str, mkdirs: bool = True, overwrite: bool = True
    ) -> Tuple[Path, dict]:
        """
        Downloads a file from the MinIO bucket to a specified destination path.
        Args:
            key (str): The key of the file in the MinIO bucket.
            dest_path (str): The local destination path where the file will be saved.
            mkdirs (bool, optional): Whether to create parent directories for the destination path if they do not exist. Defaults to True.
            overwrite (bool, optional): Whether to overwrite the file at the destination path if it already exists. Defaults to True.
        Returns:
            Tuple[Path, dict]: A tuple containing:
                - The Path object of the downloaded file.
                - A dictionary with metadata about the file, including:
                    - "size" (int): The size of the file in bytes.
                    - "etag" (str): The entity tag of the file.
                    - "content_type" (str or None): The content type of the file, if available.
                    - "last_modified" (str or None): The last modified timestamp of the file in ISO 8601 format, if available.
        Raises:
            FileExistsError: If the destination file exists and `overwrite` is set to False.
            RuntimeError: If the file download fails due to an S3Error.
        """

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