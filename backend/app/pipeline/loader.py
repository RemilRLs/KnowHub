from pathlib import Path
from typing import List, Dict
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredPowerPointLoader,
    TextLoader,
)

LOADER_MAPPING = {
    ".pdf": PyPDFLoader,
    ".docx": UnstructuredWordDocumentLoader,
    ".pptx": UnstructuredPowerPointLoader,
    ".txt": TextLoader,
}


class DocumentLoader:
    def __init__(self, default_collection: str = "default"):
        """
        Minimal loader for PDF.
        Will be improve later
        """

    def load_documents(self, file_paths: List[Path]) -> List[Document]:
        """
        Load documents from the given file paths.
        """

        all_docs: List[Document] = []

        for file_path in file_paths:

            file_path = Path(file_path) # To avoid issues (such as path traversal attacks).
            ext = file_path.suffix.lower()
            if not file_path.exists() or not file_path.is_file():
                raise FileNotFoundError(f"File not found: {file_path}")
            if file_path.suffix.lower() not in LOADER_MAPPING:
                raise ValueError(f"Unsupported file type: {file_path.suffix}")

            loader_cls = LOADER_MAPPING[ext]
            loader = loader_cls(str(file_path))
            docs = loader.load()
            all_docs.extend(docs)

        print(f"Docs raw  {all_docs}")
        return all_docs