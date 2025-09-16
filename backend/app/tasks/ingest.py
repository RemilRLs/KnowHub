import dramatiq
import tempfile

from pathlib import Path

from . import results_backend

from app.core.minio_client import MinioClient
from app.pipeline.loader import DocumentLoader

minio_client = MinioClient()


@dramatiq.actor(store_results=True, max_retries=3)
def ingest_document(doc_id: str, s3_key: str, filename: str, collection: str):
    with tempfile.TemporaryDirectory(prefix="ingest_") as tmpdir:
        local_path = Path(tmpdir) / filename
        local_path.parent.mkdir(parents=True, exist_ok=True)

        downloaded_path, meta = minio_client.get_file(
            key=s3_key,
            dest_path=str(local_path),
        )

        # Check hash (SHA-256) here later.
        # Check file type here later.


        # Maybe one day antivirus scan here later.

        loader = DocumentLoader()
        docs = loader.load_documents([downloaded_path])
    
        # Then promote the file put it in "processed " location S3.

        return {"ok": True, 
                "doc_id": doc_id, 
                "local_path": str(downloaded_path),
                "docs": len(docs),
                "meta": meta, 
                "collection": collection}
    



"""
# app/tasks/ingest.py
import dramatiq, tempfile, hashlib
from pathlib import Path
from minio.commonconfig import CopySource

from app.core.minio_client import MinioClient
from app.pipeline.loader import DocumentLoader

minio = MinioClient()

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def _assert_pdf(path: Path, min_size=1024):
    # ajoute un test magic bytes si tu veux (python-magic)
    if path.stat().st_size < min_size:
        raise ValueError(f"Object too small ({path.stat().st_size} bytes)")

@dramatiq.actor(store_results=True, max_retries=3, queue_name="ingest-validate")
def validate_and_promote(doc_id: str, s3_key: str, filename: str, collection: str, checksum_sha256: str | None = None):
    # 1) Download from quarantine
    with tempfile.TemporaryDirectory(prefix="ingest_") as tmpdir:
        local = Path(tmpdir) / filename
        downloaded_path, meta = minio.get_file(key=s3_key, dest_path=str(local))

        # 2) Validations
        _assert_pdf(downloaded_path)
        if checksum_sha256:
            if _sha256(downloaded_path).lower() != checksum_sha256.lower():
                raise ValueError("Checksum mismatch")

        # (optionnel) antivirus ici

        # 3) Promote (server-side copy)
        processed_key = s3_key.replace("incoming/", "processed/", 1) if s3_key.startswith("incoming/") \
                        else s3_key.replace("uploads/", "processed/", 1)
        minio.client.copy_object(minio.bucket, processed_key, CopySource(minio.bucket, s3_key))
        minio.client.remove_object(minio.bucket, s3_key)

        # 4) Enchaîner l’indexation
        next_msg = index_document.send(
            doc_id=doc_id,
            s3_key=processed_key,
            filename=filename,
            collection=collection,
        )

        # stocker les deux IDs pour le suivi
        return {
            "stage": "validated",
            "doc_id": doc_id,
            "processed_key": processed_key,
            "next_job_id": next_msg.message_id,
            "meta": {"size": meta.get("size"), "etag": meta.get("etag")},
        }

@dramatiq.actor(store_results=True, max_retries=3, queue_name="ingest-index")
def index_document(doc_id: str, s3_key: str, filename: str, collection: str):
    # 1) Download (depuis processed/)
    with tempfile.TemporaryDirectory(prefix="index_") as tmpdir:
        local = Path(tmpdir) / filename
        downloaded_path, meta = minio.get_file(key=s3_key, dest_path=str(local))

        # 2) Load + (plus tard) split/embeddings/upsert
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

"""