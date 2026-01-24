import logging

from contextlib import contextmanager
from typing import List, Dict, Any
from pathlib import Path

from app.pipeline.loader import DocumentLoader
from app.pipeline.normalize import DocumentNormalizer
from app.pipeline.splitter import DocumentSplitter
from langchain_core.documents import Document

from app.core.pgvector.pgvector import PgVectorStore
from app.config.config import PGVECTOR_DSN

logger = logging.getLogger(__name__)

class IngestPipeline:
    def __init__(self, 
                 loader: DocumentLoader,
                 dsn: str = PGVECTOR_DSN
                 ):
        self.loader = loader
        self.dsn = dsn

    @contextmanager
    def _get_vectorstore(self):
        """
        Context manager to get a PgVectorStore connection
        and free it after use.
        """
        store = PgVectorStore(dsn=self.dsn)
        try:
            yield store
        finally:
            store.pg_pool.disconnect() # We close the connection pool.


    def ingest(
        self,
        file_paths: List[str | Path],
        doc_id: str,
        processed_key: str,
        collection: str,
    ) -> Dict[str, Any]:
        """
        
        """
        logger.info("Ingest: loading %d file(s)", len(file_paths))
        paths = [Path(p) for p in file_paths]

        # Read and load documents
        loaded_docs = self.loader.load_documents(paths)
        logger.info("Ingest: loaded %d document(s)", len(loaded_docs))

        enriched_docs: List[Document] = []
        for doc in loaded_docs:
            meta = dict(doc.metadata or {})
            meta["doc_id"] = doc_id
            meta["processed_key"] = processed_key
            meta["url"] = processed_key
            enriched_docs.append(Document(page_content=doc.page_content, metadata=meta))

        if not loaded_docs:
            logger.warning("No documents loaded, skipping ingestion.")
            return {
                "doc_id": doc_id, 
                "collection": collection,
                "chunks_inserted": 0
            }

        # Normalize document text
        normalizer = DocumentNormalizer()
        normalized_docs = normalizer.normalize(enriched_docs)
        logger.info("Ingest: normalized %d document(s)", len(normalized_docs))

        # Split documents into smaller chunks
        splitter = DocumentSplitter()
        split_docs = splitter.split(normalized_docs)
        logger.info("Ingest: split into %d chunk(s)", len(split_docs))

        # Store chunks into PgVector
        with self._get_vectorstore() as pgvector_store:
            if not pgvector_store.table_exists(collection):
                pgvector_store.create_vector_collection(
                                                        collection_name=collection,
                                                        index_type="hnsw"
                                                    )

            pgvector_store.insert_chunks(
                                        collection=collection, 
                                        docs=split_docs
                                        )

        return {
            "doc_id": doc_id,
            "collection": collection,
            "documents": normalized_docs,
            "chunks_count": len(split_docs),
        }


    # All the step for RAG ingestion
    # - Load document
    # - Split document
    # - Create embeddings
    # - Store in vector DB
