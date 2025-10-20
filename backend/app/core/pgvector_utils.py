from typing import Any, Callable, List, Optional, Tuple, Dict
import time
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class PgVectorUtils:
    def __init__(self, embed_endpoint="http://localhost:8000/api/v1/ingest/embed"):
        self.embed_endpoint = embed_endpoint
        

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Computes embeddings for a list of texts via the embedding API.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            RuntimeError: If the embedding service is not accessible
        """
        if not texts:
            return []

        try:
            response = requests.post(
                self.embed_endpoint,
                json={"texts": texts},
                timeout=120
            )
            response.raise_for_status()
            data = response.json()

            if "embeddings" not in data:
                raise ValueError("Invalid response: 'embeddings' field is missing")

            return data["embeddings"]

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error while calling the embedding service: {e}")
    
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
