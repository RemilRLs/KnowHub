from typing import Any, Callable, List, Optional, Tuple, Dict


class PgVectorUtils:
    def __init__(self
                 # embed_func: Callable[[List[str]], List[List[float]]]
                 ):
        # self.embed_func = embed_func
        pass

    def prepare_chunks(
            self,
            docs: List[Any],
    ) -> Tuple[List[str], List[str], List[Optional[int]], List[List[float]]]:
        
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
        # embeddings: List[List[float]] = self.embed_func(texts) if texts else []

        return texts, metadatas # , embeddings