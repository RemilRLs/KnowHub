import logging

from typing import Any, List, Tuple, Dict
from app.core.qwen_embedder import get_embedder

logger = logging.getLogger(__name__)

class PgVectorUtils:
    def __init__(self, embed_endpoint="http://api:8000/api/v1/ingest/embed"):
        self.embed_endpoint = embed_endpoint
        self.embedder = get_embedder()

    def embed(self, texts: List[str]) -> List[List[float]]:
        return self.embedder.embed(texts)
    
    def prepare_chunks(
            self,
            docs: List[Any],
    ) -> Tuple[List[str], List[Dict[str, Any]], List[List[float]]]:
        
        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        ALLOWED_KEYS = {"page", "ext", "file_name", "file_sha256", "ingested_at"}

        for d in docs:
            text = (d.page_content or "").strip()
            if not text:
                continue

            raw_meta = dict(d.metadata or {})

            meta = {k: raw_meta.get(k) for k in ALLOWED_KEYS if k in raw_meta}

            meta.setdefault("file_name", "unknown")
            meta.setdefault("page", 0)
            meta.setdefault("ext", "txt")

            texts.append(text)
            metadatas.append(meta)
        print(f"Computing embeddings for {len(texts)} texts")

        embeddings: List[List[float]] = self.embed(texts) if texts else []

        if embeddings:
            print(f"Got embeddings: {len(embeddings)} vectors of size {len(embeddings[0])}")

        return texts, metadatas, embeddings
