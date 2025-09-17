import logging

import dramatiq
import tempfile

from dramatiq.middleware import SkipMessage

from pathlib import Path

from . import results_backend

from app.core.minio_client import MinioClient
from minio.commonconfig import CopySource

from app.core.hash_utils import verify_sha256
from app.core.settings import Settings

from app.pipeline.loader import DocumentLoader


logger = logging.getLogger(__name__)
minio_client = MinioClient()


class IngestError(Exception):
    pass

@dramatiq.actor(store_results=True, max_retries=0, queue_name="ingest-validate")
def validate_and_promote(doc_id: str, 
                         s3_key: str, 
                         filename: str, 
                         collection: str, 
                         checksum_sha256: str
                         ):
    with tempfile.TemporaryDirectory(prefix="ingest_") as tmpdir:
        local = Path(tmpdir) / filename
        download_path, meta = minio_client.get_file(
            key=s3_key,
            dest_path=str(local)
        )

        # Check file type here later.

        if not verify_sha256(download_path, checksum_sha256):
            logger.error(f"Checksum mismatch for doc_id={doc_id}")

            minio_client.client.remove_object(minio_client.bucket, s3_key)
            raise ValueError("Checksum mismatch")
        
        logger.info(f"Checksum verified for doc_id={doc_id}, promoting to processed/")

        processed_key = s3_key.replace("uploads/", "processed/", 1)

        # Copy to processed/ then remove uploads/
        minio_client.client.copy_object(
            minio_client.bucket,
            processed_key,
            CopySource(minio_client.bucket, s3_key)
        )
        minio_client.client.remove_object(minio_client.bucket, s3_key)

        # Enqueue next step
        next_msg = ingest_document.send(
            doc_id=doc_id,
            s3_key=processed_key,
            filename=filename,
            collection=collection,
        )

        return {
            "stage": "validated",
            "doc_id": doc_id,
            "processed_key": processed_key,
            "next_job_id": next_msg.message_id,
            "meta": {"size": meta.get("size"), "etag": meta.get("etag")},
        }

@dramatiq.actor(store_results=True, max_retries=3, queue_name="ingest-process", throws=(IngestError,))
def ingest_document(doc_id: str, 
                    s3_key: str, 
                    filename: str, 
                    collection: str
                    ):
    
    allowed_extensions = Settings.get_allowed_extensions()
    file_extension = Path(filename).suffix.lower()

    if file_extension not in allowed_extensions:
        logger.error(f"File extension not allowed: {filename}")
        raise IngestError(f"File extension not allowed: {filename}")
    
    with tempfile.TemporaryDirectory(prefix="ingest_") as tmpdir:
        local_path = Path(tmpdir) / filename
        local_path.parent.mkdir(parents=True, exist_ok=True)

        downloaded_path, meta = minio_client.get_file(
            key=s3_key,
            dest_path=str(local_path),
        )

        loader = DocumentLoader()
        docs = loader.load_documents([downloaded_path])

        # TODO: split -> embeddings -> upsert pgvector here

        return {
            "stage": "indexed",
            "doc_id": doc_id,
            "processed_key": s3_key,
            "pages_loaded": len(docs),
            "collection": collection,
        }