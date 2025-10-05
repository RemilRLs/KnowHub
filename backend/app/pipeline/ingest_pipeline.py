import logging

from typing import List, Dict, Any
from pathlib import Path

from app.pipeline.loader import DocumentLoader
from app.pipeline.normalize import DocumentNormalizer
from app.pipeline.splitter import DocumentSplitter

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class IngestPipeline:
    def __init__(self, 
                 loader: DocumentLoader):
        self.loader = loader

    def ingest(
        self,
        file_paths: List[str | Path],
        doc_id: str,
        collection: str,
    ) -> Dict[str, Any]:
        """
        
        """
        logger.info("Ingest: loading %d file(s)", len(file_paths))
        paths = [Path(p) for p in file_paths]
        loaded_docs = self.loader.load_documents(paths)
        logger.info("Ingest: loaded %d document(s)", len(loaded_docs))

        normalizer = DocumentNormalizer()
        normalized_docs = normalizer.normalize(loaded_docs)

        splitter = DocumentSplitter()
        split_docs = splitter.split(normalized_docs)

        return {
            "doc_id": doc_id,
            "collection": collection,
            "documents": normalized_docs,
        }


    # All the step for RAG ingestion
    # - Load document
    # - Split document
    # - Create embeddings
    # - Store in vector DB