import logging

from app.core.hash_utils import compute_sha256

from pathlib import Path
from typing import List, Optional, Dict
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredPowerPointLoader,
    UnstructuredMarkdownLoader,
    TextLoader,
)

logger = logging.getLogger(__name__)

LOADER_MAPPING = {
    ".pdf": PyPDFLoader,
    ".docx": UnstructuredWordDocumentLoader,
    ".pptx": UnstructuredPowerPointLoader,
    ".txt": TextLoader,
    ".md": UnstructuredMarkdownLoader,
}



class DocumentLoader:
    def __init__(
        self,
        default_collection: str = "default",
        max_file_size_bytes: Optional[int] = 50 * 1024 * 1024,  # 50 MB
    ):

        self.default_collection = default_collection
        self.max_file_size_bytes = max_file_size_bytes

    def _validate_file(self, file_path: Path) -> str:
        """
        
        """

        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        if self.max_file_size_bytes is not None and file_path.stat().st_size > self.max_file_size_bytes:
            raise ValueError(f"File too large: {file_path} exceeds {self.max_file_size_bytes} bytes")
        
        ext = file_path.suffix.lower()
        if ext not in LOADER_MAPPING:
            raise ValueError(f"Unsupported file type: {ext}")

        return ext
    
    def _load_one(self, file_path: Path) -> List[Document]:
        """Load a single file with the proper loader."""
        p = Path(file_path).resolve()
        ext = self._validate_file(p)
        loader_cls = LOADER_MAPPING[ext]
        loader = loader_cls(str(p))
        docs = loader.load()
        return docs

    def load_documents(self, file_paths: List[Path]) -> List[Document]:
        """
        Load documents from the given file paths.
        """

        all_docs: List[Document] = []



        for file_path in file_paths:
            try:
                p = Path(file_path)
                docs = self._load_one(p)
                if not isinstance(docs, list):
                    logger.warning("Loader for %s returned %r, coercing to []", p, type(docs))
                    docs = []

                logger.info("Loaded %d document(s) from %s", len(docs), p)

                file_hash = compute_sha256(p)

                enriched_docs: List[Document] = []
                for d in docs:
                    meta = dict(d.metadata or {})
                    meta["file_sha256"] = file_hash
                    enriched_docs.append(Document(page_content=d.page_content, metadata=meta))

                all_docs.extend(enriched_docs)

            except Exception as e:
                logger.exception("Error loading %s: %s", file_path, e)
                continue

        return all_docs