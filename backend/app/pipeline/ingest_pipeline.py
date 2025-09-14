from typing import List, Dict
from app.pipelines.loader import DocumentLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

class IngestPipeline:
    pass

    # All the step for RAG ingestion
    # - Load document
    # - Split document
    # - Create embeddings
    # - Store in vector DB