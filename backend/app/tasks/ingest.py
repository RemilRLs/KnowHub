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

        loader = DocumentLoader()
        docs = loader.load_documents([downloaded_path])

        return {"ok": True, 
                "doc_id": doc_id, 
                "local_path": str(downloaded_path),
                "docs": len(docs),
                "meta": meta, 
                "collection": collection}